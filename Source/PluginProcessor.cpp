#include "PluginProcessor.h"
#include "PluginEditor.h"

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withOutput("Output", juce::AudioChannelSet::mono(), true)),
      apvts(*this, nullptr, "PARAMETERS", createParameterLayout())
{
}

juce::AudioProcessorValueTreeState::ParameterLayout VstAiDemoAudioProcessor::createParameterLayout()
{
    std::vector<std::unique_ptr<juce::RangedAudioParameter>> params;
    
    // Delay Time: 1 to 2000 ms, default 500 ms
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "delayTime",
        "Delay Time",
        juce::NormalisableRange<float>(1.0f, 2000.0f),
        500.0f));
    
    // Wet/Dry Mix: 0 to 100 %, default 50 %
    params.push_back(std::make_unique<juce::AudioParameterFloat>(
        "dryWetMix",
        "Dry/Wet Mix",
        juce::NormalisableRange<float>(0.0f, 100.0f),
        50.0f));
    
    return { params.begin(), params.end() };
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    juce::ignoreUnused(samplesPerBlock);
    currentSampleRate = sampleRate;
    
    // Initialize delay line with maximum delay (2 seconds for 2000 ms)
    delayLine.prepare({ sampleRate, static_cast<juce::uint32>(samplesPerBlock), 1 });
    delayLine.setMaximumDelayInSamples(static_cast<int>(sampleRate * 2.0));
}

void VstAiDemoAudioProcessor::releaseResources()
{
    delayLine.reset();
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto input = layouts.getMainInputChannelSet();
    const auto output = layouts.getMainOutputChannelSet();
    return input == output && output == juce::AudioChannelSet::mono();
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midiMessages)
{
    juce::ignoreUnused(midiMessages);
    juce::ScopedNoDenormals noDenormals;
    
    auto totalNumInputChannels = getTotalNumInputChannels();
    auto totalNumOutputChannels = getTotalNumOutputChannels();
    
    for (auto i = totalNumInputChannels; i < totalNumOutputChannels; ++i)
        buffer.clear(i, 0, buffer.getNumSamples());
    
    // Get parameter values
    float delayTimeMs = apvts.getRawParameterValue("delayTime")->load();
    float dryWetMixPercent = apvts.getRawParameterValue("dryWetMix")->load();
    
    // Convert delay time from ms to samples
    float delaySamples = (delayTimeMs / 1000.0f) * static_cast<float>(currentSampleRate);
    delayLine.setDelay(delaySamples);
    
    // Convert mix percentage to 0-1 range (100% = fully wet, 0% = fully dry)
    float wetGain = dryWetMixPercent / 100.0f;
    float dryGain = 1.0f - wetGain;
    
    // Process the mono channel
    if (totalNumInputChannels > 0)
    {
        auto* channelData = buffer.getWritePointer(0);
        int numSamples = buffer.getNumSamples();
        
        for (int i = 0; i < numSamples; ++i)
        {
            float drySignal = channelData[i];
            float delayedSignal = delayLine.popSample(0);
            delayLine.pushSample(0, drySignal);
            
            channelData[i] = (drySignal * dryGain) + (delayedSignal * wetGain);
        }
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto xml = apvts.state.createXml();
    if (xml != nullptr)
        copyXmlToBinary(*xml, destData);
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState != nullptr && xmlState->hasTagName(apvts.state.getType()))
        apvts.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
