#include "PluginProcessor.h"
#include "PluginEditor.h"

VstAiDemoAudioProcessor::VstAiDemoAudioProcessor()
    : AudioProcessor(BusesProperties()
          .withInput("Input", juce::AudioChannelSet::mono(), true)
          .withOutput("Output", juce::AudioChannelSet::mono(), true)),
      apvts(*this, nullptr, "PARAMETERS",
            {
                std::make_unique<juce::AudioParameterFloat>(
                    juce::ParameterID{ "decay", 1 },
                    "Decay",
                    juce::NormalisableRange<float>(0.0f, 1.0f),
                    0.5f)
            })
{
}

void VstAiDemoAudioProcessor::prepareToPlay(double sampleRate, int)
{
    reverb.setSampleRate(sampleRate);
}

void VstAiDemoAudioProcessor::releaseResources()
{
}

bool VstAiDemoAudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    const auto input = layouts.getMainInputChannelSet();
    const auto output = layouts.getMainOutputChannelSet();
    return input == output && output == juce::AudioChannelSet::mono();
}

void VstAiDemoAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                            juce::MidiBuffer& midiMessages)
{
    juce::ScopedNoDenormals noDenormals;
    juce::ignoreUnused(midiMessages);

    auto decayParam = apvts.getRawParameterValue("decay");
    juce::Reverb::Parameters params;
    params.decay = decayParam->load();

    reverb.setParameters(params);

    if (buffer.getNumChannels() > 0)
    {
        reverb.processMono(buffer.getWritePointer(0), buffer.getNumSamples());
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
    if (xmlState.get() != nullptr)
    {
        auto state = juce::ValueTree::fromXml(*xmlState);
        apvts.replaceState(state);
    }
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new VstAiDemoAudioProcessor();
}
