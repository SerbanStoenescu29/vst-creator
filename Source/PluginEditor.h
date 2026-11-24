#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"

class VstAiDemoAudioProcessorEditor final : public juce::AudioProcessorEditor
{
public:
    explicit VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor&);
    ~VstAiDemoAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    VstAiDemoAudioProcessor& processor;

    juce::Label titleLabel;
    juce::Label decayLabel;
    juce::Slider decaySlider;
    std::unique_ptr<juce::SliderParameterAttachment> decayAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(VstAiDemoAudioProcessorEditor)
};
