#include "PluginProcessor.h"
#include "PluginEditor.h"

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::stereo(), true)
          .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      apvts(*this, nullptr, "PARAMETERS", createParameterLayout())
{
}

juce::AudioProcessorValueTreeState::ParameterLayout VstAiDemoAudioProcessor::createParameterLayout()
{
    juce::AudioProcessorValueTreeState::ParameterLayout layout;

    layout.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID("delayTime", 1),
        "Delay Time",
        juce::NormalisableRange<float>(0.0f, 3000.0f, 50.0f),
        500.0f));

    layout.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID("feedback", 1),
        "Repeats",
        juce::NormalisableRange<float>(0.0f, 100.0f, 1.0f),
        30.0f));

    layout.add(std::make_unique<juce::AudioParameterFloat>(
        juce::ParameterID("mix", 1),
        "Wet/Dry Mix",
        juce::NormalisableRange<float>(0.0f, 100.0f, 1.0f),
        50.0f));

    return layout;
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    juce::ignoreUnused(samplesPerBlock);
    
    int maxDelaySamples = static_cast<int>((MAX_DELAY_MS / 1000.0) * sampleRate) + 1;
    delayLine.setMaximumDelayInSamples(maxDelaySamples);
}

void VstAiDemoAudioProcessor::releaseResources()
{
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto input = layouts.getMainInputChannelSet();
    const auto output = layouts.getMainOutputChannelSet();
    return input == output &&
           (output == juce::AudioChannelSet::mono() ||
            output == juce::AudioChannelSet::stereo());
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                            juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);
    
    float delayTimeMs = apvts.getRawParameterValue("delayTime")->load();
    float feedbackPercent = apvts.getRawParameterValue("feedback")->load();
    float mixPercent = apvts.getRawParameterValue("mix")->load();
    
    float delayTimeSamples = (delayTimeMs / 1000.0f) * static_cast<float>(getSampleRate());
    float feedback = feedbackPercent / 100.0f;
    float mix = mixPercent / 100.0f;
    
    delayLine.setDelay(delayTimeSamples);
    
    int numChannels = buffer.getNumChannels();
    int numSamples = buffer.getNumSamples();
    
    for (int channel = 0; channel < numChannels; ++channel)
    {
        float* channelData = buffer.getWritePointer(channel);
        
        for (int sample = 0; sample < numSamples; ++sample)
        {
            float input = channelData[sample];
            float delayedSample = delayLine.popSample(channel);
            
            float output = input + (delayedSample * feedback);
            
            channelData[sample] = input * (1.0f - mix) + output * mix;
            
            delayLine.pushSample(channel, output);
        }
    }
}

juce::AudioProcessorEditor* VstAiDemoAudioProcessor::createEditor()
{
    return new VstAiDemoAudioProcessorEditor(*this);
}

void VstAiDemoAudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    auto state = apvts.copyStateToValueTree();
    std::unique_ptr<juce::XmlElement> xml(state.createXml());
    copyXmlToBinary(*xml, destData);
}

void VstAiDemoAudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    std::unique_ptr<juce::XmlElement> xmlState(getXmlFromBinary(data, sizeInBytes));
    if (xmlState != nullptr)
        apvts.replaceState(juce::ValueTree::fromXml(*xmlState));
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
